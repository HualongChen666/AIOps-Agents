// 示例：Get workflow
fetch('http://localhost:8080/api/v1/workflows/{workflow_id}', {
    method: 'GET'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
