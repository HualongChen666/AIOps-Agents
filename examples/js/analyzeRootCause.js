// 示例：Analyze root cause
fetch('http://localhost:8080/api/v1/anomalies/{anomaly_id}/root-cause', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
