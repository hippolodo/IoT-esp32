package com.iot.backend.controller;

import com.iot.backend.dto.ApiResponse;
import com.iot.backend.entity.User;
import com.iot.backend.repository.UserRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * User Controller - API quản lý thông tin người dùng
 * Endpoints: /api/user
 */
@Slf4j
@RestController
@RequestMapping("/api/user")
@CrossOrigin(origins = "*")
public class UserController {

    @Autowired
    private UserRepository userRepository;

    /**
     * Lấy thông tin user hiện tại (Mặc định lấy user admin)
     * GET /api/user/profile
     */
    @GetMapping("/profile")
    public ResponseEntity<ApiResponse<User>> getProfile() {
        try {
            return userRepository.findByUsername("admin")
                    .map(user -> ResponseEntity.ok(ApiResponse.success(user, "Lấy thông tin user thành công")))
                    .orElseGet(() -> ResponseEntity.status(404)
                            .body(ApiResponse.error("Không tìm thấy user", 404)));
        } catch (Exception e) {
            log.error("Lỗi lấy thông tin user: ", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("Lỗi lấy thông tin user", 500));
        }
    }
}