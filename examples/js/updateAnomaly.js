// 示例：Update anomaly
fetch('http://localhost:8080/api/v1/anomalies/{anomaly_id}', {
    method: 'PUT'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
