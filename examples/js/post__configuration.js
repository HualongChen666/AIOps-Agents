// 示例：POST /configuration
fetch('http://localhost:8080/api/v1/configuration', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
