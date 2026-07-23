// 示例：PATCH /{alert_id}
fetch('http://localhost:8080/api/v1/{alert_id}', {
    method: 'PATCH'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
