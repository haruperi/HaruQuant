from apps.logger import logger

def main():
    print("--- Rotation and Retention Examples ---")
    
    # NOTE: These examples define handlers but don't actively rotate 
    # without filling them with data or time passing. 
    # They demonstrate API syntax validity.

    print("Configuring size-based rotation...")
    # Rotate when file reaches 10 MB
    logger.add("logs/rotate_size_10mb.log", rotation="10 MB")
    
    # Rotate when file reaches 500 MB
    logger.add("logs/rotate_size_500mb.log", rotation="500 MB")
    
    # Rotate when file reaches 1 GB
    logger.add("logs/rotate_size_1gb.log", rotation="1 GB")

    print("Configuring time-based rotation...")
    # Rotate daily at midnight
    logger.add("logs/rotate_daily_midnight.log", rotation="00:00")
    
    # Rotate daily at 12:00
    logger.add("logs/rotate_daily_noon.log", rotation="12:00")
    
    # Rotate weekly on Monday
    logger.add("logs/rotate_weekly_monday.log", rotation="1 week")
    
    # Rotate monthly
    logger.add("logs/rotate_monthly.log", rotation="1 month")
    
    print("Configuring retention...")
    # Keep logs for 7 days
    logger.add("logs/retention_7days.log", retention="7 days")
    
    # Keep logs for 30 days
    logger.add("logs/retention_30days.log", retention="30 days")
    
    # Keep last 10 files
    logger.add("logs/retention_count.log", retention=10)
    
    print("Configuring compression...")
    # Compress with zip
    logger.add("logs/compress_zip.log", rotation="500 MB", compression="zip")
    
    # Compress with gzip
    logger.add("logs/compress_gzip.log", rotation="1 GB", compression="gz")

    print("Configuration complete. (No actual rotation triggered in this script)")

if __name__ == "__main__":
    main()
