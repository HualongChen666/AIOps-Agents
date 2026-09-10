const anomalyId = 'YOUR_ANOMALY_ID';
const authToken = process.env.AIOPS_TOKEN || 'YOUR_TOKEN';
// 示例：Delete anomaly
fetch(`http://localhost:8000/api/v1/anomalies/${anomalyId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${authToken}` }
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
