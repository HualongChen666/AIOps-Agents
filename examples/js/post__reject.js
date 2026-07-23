// 示例：POST /reject
fetch('http://localhost:8080/api/v1/reject', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
