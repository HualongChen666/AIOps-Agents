// 示例：GET /pending
fetch('http://localhost:8080/api/v1/pending', {
    method: 'GET'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
