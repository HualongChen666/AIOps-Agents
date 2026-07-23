// 示例：POST /database
fetch('http://localhost:8080/api/v1/database', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
