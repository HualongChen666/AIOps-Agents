const alertId = 'YOUR_ALERT_ID';
const authToken = process.env.AIOPS_TOKEN || 'YOUR_TOKEN';
// 示例：PATCH /{alert_id}
fetch(`http://localhost:8000/api/v1/${alertId}`, {
    method: 'PATCH',
    headers: { Authorization: `Bearer ${authToken}` }
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
