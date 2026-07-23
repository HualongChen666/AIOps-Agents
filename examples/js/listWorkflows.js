// 示例：List workflows
fetch('http://localhost:8080/api/v1/workflows', {
    method: 'GET'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
