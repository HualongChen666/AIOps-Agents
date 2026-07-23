// 示例：GET /intelligence/statistics
fetch('http://localhost:8080/api/v1/intelligence/statistics', {
    method: 'GET'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
