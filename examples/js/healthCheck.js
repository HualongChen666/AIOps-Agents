// 示例：Health check
fetch('http://localhost:8080/api/v1/health', {
    method: 'GET'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
