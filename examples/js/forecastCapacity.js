// 示例：Forecast capacity
fetch('http://localhost:8080/api/v1/capacity/forecast', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
