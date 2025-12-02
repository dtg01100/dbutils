-- Example query demonstrating various SQL features
SELECT 
    u.user_id,
    u.username,
    u.email,
    COUNT(o.order_id) as order_count,
    SUM(o.total_amount) as total_spent
FROM 
    users u
JOIN 
    orders o ON u.user_id = o.user_id
WHERE 
    u.status = 'active'
    AND o.order_date >= '2024-01-01'
GROUP BY 
    u.user_id, u.username, u.email
HAVING 
    COUNT(o.order_id) > 5
ORDER BY 
    total_spent DESC
LIMIT 100;
