// 示例：POST /predict/time-series
fetch('http://localhost:8080/api/v1/predict/time-series', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
