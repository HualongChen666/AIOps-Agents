// 示例：Forecast cost
fetch('http://localhost:8080/api/v1/cost/forecast', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
