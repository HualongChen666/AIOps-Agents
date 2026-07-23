// 示例：GET /intelligence/patterns
fetch('http://localhost:8080/api/v1/intelligence/patterns', {
    method: 'GET'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
