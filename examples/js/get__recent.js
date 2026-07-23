// 示例：GET /recent
fetch('http://localhost:8080/api/v1/recent', {
    method: 'GET'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
