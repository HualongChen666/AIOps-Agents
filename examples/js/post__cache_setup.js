// 示例：POST /cache/setup
fetch('http://localhost:8080/api/v1/cache/setup', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
