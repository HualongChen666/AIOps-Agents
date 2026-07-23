// 示例：POST /optimize
fetch('http://localhost:8080/api/v1/optimize', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
