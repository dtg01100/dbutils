-- Get customers by salesperson who are missing any license (cig, tobacco, or other)
SELECT 
    TRIM(dsadrep.adbbtx) AS "Salesperson Name",
    dsabrep.ababnb AS "Customer Number",
    TRIM(dsabrep.abaatx) AS "Customer Name",
    dsabrep.abbvst AS "Customer Status",
    dsabrep.abbjtx AS "Cig License",
    dsabrep.abbktx AS "Tobacco License",
    dsabrep.abbltx AS "Other License",
    TRIM(dsabrep.ababtx) AS "Customer Address",
    TRIM(dsabrep.abaetx) AS "Customer Town",
    TRIM(dsabrep.abaftx) AS "Customer State",
    TRIM(dsabrep.abagtx) AS "Customer Zip"
FROM 
    dacdata.dsabrep dsabrep
    INNER JOIN dacdata.dsadrep dsadrep ON dsabrep.abajcd = dsadrep.adaecd
WHERE 
    -- Filter for customers missing any license type
    (dsabrep.abbjtx IS NULL OR TRIM(dsabrep.abbjtx) = '' OR dsabrep.abbjtx = ' ')  -- Missing Cig License
    OR 
    (dsabrep.abbktx IS NULL OR TRIM(dsabrep.abbktx) = '' OR dsabrep.abbktx = ' ')  -- Missing Tobacco License
    OR 
    (dsabrep.abbltx IS NULL OR TRIM(dsabrep.abbltx) = '' OR dsabrep.abbltx = ' ')  -- Missing Other License
ORDER BY 
    TRIM(dsabrep.abaftx),
    TRIM(dsadrep.adbbtx),
    TRIM(dsabrep.abaatx)