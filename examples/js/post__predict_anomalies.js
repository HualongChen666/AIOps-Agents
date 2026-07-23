// 示例：POST /predict/anomalies
fetch('http://localhost:8080/api/v1/predict/anomalies', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
