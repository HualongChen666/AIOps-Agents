// 示例：List backups
fetch('http://localhost:8080/api/v1/backup/list', {
    method: 'GET'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
