from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report
import io


app = Flask(__name__)
CORS(app)  

def detect_anomalies(df):
    df["As of Date"] = pd.to_datetime(df["As of Date"])
    df = df.sort_values(by=["Account", "Primary Account", "Secondary Account", "AU", "As of Date"])
    df["Balance Difference Lag1"] = df.groupby(["Account", "Primary Account", "Secondary Account", "AU"])["Balance Difference"].shift(1)
    df["Balance Difference Lag2"] = df.groupby(["Account", "Primary Account", "Secondary Account", "AU"])["Balance Difference"].shift(2)
    df["Rolling Mean"] = df.groupby(["Account", "Primary Account", "Secondary Account", "AU"])["Balance Difference"].rolling(window=3).mean().reset_index(drop=True)
    df["Rolling Std"] = df.groupby(["Account", "Primary Account", "Secondary Account", "AU"])["Balance Difference"].rolling(window=3).std().reset_index(drop=True)
    df.fillna(0, inplace=True)
    encoder = LabelEncoder()
    df["Account Encoded"] = encoder.fit_transform(df["Account"].astype(str))
    df["Primary Account Encoded"] = encoder.fit_transform(df["Primary Account"].astype(str))
    df["Secondary Account Encoded"] = encoder.fit_transform(df["Secondary Account"].astype(str))
    df["AU Encoded"] = encoder.fit_transform(df["AU"].astype(str))

    df["Anomaly"] = np.where(
        (df["Match Status"] == "Break") & 
        (abs(df["Balance Difference"] - df["Rolling Mean"]) > 2 * df["Rolling Std"]), 1, 0
    )
    df = df.dropna(subset=["Balance Difference Lag1", "Rolling Mean", "Rolling Std"])

    X = df[["Balance Difference", "Balance Difference Lag1", "Balance Difference Lag2", 
        "Rolling Mean", "Rolling Std", "Account Encoded", "Primary Account Encoded", 
        "Secondary Account Encoded", "AU Encoded"]]
    y = df["Anomaly"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42) 

    model = xgb.XGBClassifier(objective="binary:logistic", eval_metric="logloss", use_label_encoder=False)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    

    df["Predicted Anomaly"] = model.predict(X)

    def generate_comment_ml(row):
        if row["Predicted Anomaly"] == 1 and row["Match Status"] == "Break":
            if abs(row["Balance Difference"]) > (row["Rolling Mean"] + 2 * row["Rolling Std"]):
                return "Huge spike in the outstanding balance."
            else:
                return "Inconsistent deviation in the outstanding balances."
    
        elif row["Match Status"] == "Break":
            if abs(row["Balance Difference"] - row["Rolling Mean"]) < row["Rolling Std"]:
                return "Outstanding balance in line with previous data."
            else:
                return "Consistent deviation in the outstanding balances."

        else:
            return ""

    df["Comments"] = df.apply(generate_comment_ml, axis=1)
    df["Predicted Anomaly"] = df["Predicted Anomaly"].apply(lambda x: "Yes" if x == 1 else "No")
    df=df.drop(['Balance Difference Lag1','Balance Difference Lag2','Rolling Mean','Rolling Std','Account Encoded','Primary Account Encoded','Secondary Account Encoded','AU Encoded','Anomaly'],axis=1)
    return df

@app.route("/upload_csv", methods=["POST"])
def upload_csv():
    try:
        global results
        if "file" not in request.files:
            print("No file found in request") 
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]

        print(f"Received file: {file.filename}, Content-Type: {file.content_type}")

        
        file_content = file.stream.read().decode("utf-8")
        
        if not file_content.strip(): 
            return jsonify({"error": "Uploaded CSV file is empty"}), 400
        
        df = pd.read_csv(io.StringIO(file_content))

        
        results = detect_anomalies(df)
        return jsonify({"results": results.to_dict(orient="records")})

    except Exception as e:
        return jsonify({"error": str(e)})
    
@app.route("/download_csv", methods=["GET"])
def download_csv():
    global results
    if results is None:
        return jsonify({"error": "No processed file available"}), 400

    output = io.StringIO()
    results.to_csv(output, index=False)
    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="anomaly_results.csv"
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
