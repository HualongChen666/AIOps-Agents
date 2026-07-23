// 示例：Get anomaly
fetch('http://localhost:8080/api/v1/anomalies/{anomaly_id}', {
    method: 'GET'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
