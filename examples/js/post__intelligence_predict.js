// 示例：POST /intelligence/predict
fetch('http://localhost:8080/api/v1/intelligence/predict', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
