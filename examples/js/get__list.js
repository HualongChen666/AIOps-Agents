// 示例：GET /list
fetch('http://localhost:8080/api/v1/list', {
    method: 'GET'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
