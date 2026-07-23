// 示例：Create policy
fetch('http://localhost:8080/api/v1/policies', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
