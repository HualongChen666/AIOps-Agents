// 示例：GET /slow-apis
fetch('http://localhost:8080/api/v1/slow-apis', {
    method: 'GET'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
