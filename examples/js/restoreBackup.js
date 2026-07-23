// 示例：Restore backup
fetch('http://localhost:8080/api/v1/backup/restore', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
