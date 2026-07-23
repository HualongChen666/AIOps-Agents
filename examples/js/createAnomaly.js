// 示例：Create anomaly
fetch('http://localhost:8080/api/v1/anomalies', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
