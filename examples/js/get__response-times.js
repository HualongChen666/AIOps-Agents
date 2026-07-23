// 示例：GET /response-times
fetch('http://localhost:8080/api/v1/response-times', {
    method: 'GET'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
