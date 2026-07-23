// 示例：GET /intelligence/topology
fetch('http://localhost:8080/api/v1/intelligence/topology', {
    method: 'GET'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
