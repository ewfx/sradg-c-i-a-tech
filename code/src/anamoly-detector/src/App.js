import React, { useState } from "react";
import axios from "axios";

function App() {
  const [file, setFile] = useState(null);
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a CSV file first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      console.log("trying to upload file");
      const response = await axios.post("http://127.0.0.1:5000/upload_csv", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      if (response.data.error) {
        setError(response.data.error);
        setResults(null);
      } else {
        setResults(response.data.results);
        setError("");
      }
    } catch (err) {
      setError("Error uploading file.");
    }
  };

  const handleDownload = async () => {
    try {
      const response = await axios.get("http://127.0.0.1:5000/download_csv", {
        responseType: "blob",  // Important for file download
      });

      // Create a Blob URL and trigger download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "anomaly_results.csv");
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error("Error downloading file:", err);
      setError("Error downloading file.");
    }
  };

  return (
    <div style={{ textAlign: "center", padding: "20px" }}>
      <h2>Anomaly Detection Tool</h2>

      <input type="file" accept=".csv" onChange={handleFileChange} />
      <button onClick={handleUpload} style={{ marginLeft: "10px" }}>Run Anomaly Detection</button>

      {results && (
        <div>
          <h3>Data After Anomaly Detection</h3>
          <table border="1" style={{ margin: "0 auto", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {Object.keys(results[0]).map((key) => (
                  <th key={key} style={{ padding: "5px" }}>{key}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {results.slice(0, 10).map((row, index) => (
                <tr key={index}>
                  {Object.values(row).map((value, i) => (
                    <td key={i} style={{ padding: "5px" }}>{value}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>

          <button onClick={handleDownload} style={{ marginTop: "10px" }}>Download Processed File</button>
        </div>
      )}
    </div>
  );
}

export default App;