// 示例：POST /intelligence/routing-rules
fetch('http://localhost:8080/api/v1/intelligence/routing-rules', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
