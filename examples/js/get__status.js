// 示例：GET /status
fetch('http://localhost:8080/api/v1/status', {
    method: 'GET'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
