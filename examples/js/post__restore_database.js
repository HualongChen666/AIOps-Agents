// 示例：POST /restore/database
fetch('http://localhost:8080/api/v1/restore/database', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
