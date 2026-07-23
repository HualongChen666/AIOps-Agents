// 示例：Create workflow
fetch('http://localhost:8080/api/v1/workflows', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
