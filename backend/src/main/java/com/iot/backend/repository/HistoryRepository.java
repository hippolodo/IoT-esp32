package com.iot.backend.repository;

import com.iot.backend.entity.History;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;

@Repository
public interface HistoryRepository extends JpaRepository<History, Long> {
    
    // Lấy lịch sử sắp xếp theo thời gian mới nhất
    Page<History> findAllByOrderByTimestampDesc(Pageable pageable);

    @Query("SELECT h FROM History h WHERE " +
           "(:deviceId IS NULL OR h.device.id = :deviceId) AND " +
           "(:status IS NULL OR h.status = :status) AND " +
           "(:startTime IS NULL OR h.timestamp >= :startTime) AND " +
           "(:endTime IS NULL OR h.timestamp < :endTime)")
    Page<History> findByFilters(
            @Param("deviceId") Integer deviceId,
            @Param("status") String status,
            @Param("startTime") LocalDateTime startTime,
            @Param("endTime") LocalDateTime endTime,
            Pageable pageable);
    
    // Lọc lịch sử theo thiết bị, trạng thái và khoảng thời gian
    @Query("SELECT h FROM History h WHERE h.device.id = :deviceId " +
           "AND h.status = :status " +
           "AND h.timestamp BETWEEN :startTime AND :endTime " +
           "ORDER BY h.timestamp DESC")
    Page<History> findByDeviceIdAndStatusAndTimestampBetween(
            @Param("deviceId") Integer deviceId,
            @Param("status") String status,
            @Param("startTime") LocalDateTime startTime,
            @Param("endTime") LocalDateTime endTime,
            Pageable pageable);
    
    // Lấy lịch sử theo thiết bị
    Page<History> findByDeviceIdOrderByTimestampDesc(Integer deviceId, Pageable pageable);
}
