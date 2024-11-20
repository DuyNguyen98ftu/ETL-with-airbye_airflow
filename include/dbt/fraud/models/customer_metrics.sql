WITH transaction_summary AS (
    SELECT
        ct.user_id,
        COUNT(ct.transaction_id) AS total_transactions,
        SUM(CASE WHEN lt.is_fraudulent THEN 1 ELSE 0 END) AS fraudulent_transactions,
        SUM(CASE WHEN NOT lt.is_fraudulent THEN 1 ELSE 0 END) AS non_fraudulent_transactions
    FROM staging.customer_transactions ct  
    JOIN staging.labeled_transactions lt ON ct.transaction_id = lt.transaction_id
    GROUP BY ct.user_id
)
SELECT 
    user_id,
    total_transactions,
    fraudulent_transactions,
    non_fraudulent_transactions,
    CASE 
        WHEN total_transactions = 0 THEN 0
        ELSE (fraudulent_transactions::FLOAT / total_transactions) * 100
    END AS risk_score
FROM transaction_summary;
