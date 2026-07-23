// 示例：Execute auto-heal
fetch('http://localhost:8080/api/v1/autoheal/execute', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
