// 示例：Create backup
fetch('http://localhost:8080/api/v1/backup/create', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
