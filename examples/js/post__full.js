// 示例：POST /full
fetch('http://localhost:8080/api/v1/full', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
