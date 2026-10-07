package com.iot.backend.controller;

import com.iot.backend.dto.ApiResponse;
import com.iot.backend.dto.LoginRequest;
import com.iot.backend.dto.LoginResponse;
import com.iot.backend.entity.User;
import com.iot.backend.service.AuthService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Optional;

/**
 * Auth Controller - API xác thực người dùng
 * Endpoints: /api/auth
 */
@Slf4j
@RestController
@RequestMapping("/api/auth")
@CrossOrigin(origins = "*")
public class AuthController {

    @Autowired
    private AuthService authService;

    /**
     * Đăng nhập người dùng
     * POST /api/auth/login
     * 
     * @param request LoginRequest chứa username và password
     */
    @PostMapping("/login")
    public ResponseEntity<ApiResponse<LoginResponse>> login(@RequestBody LoginRequest request) {
        try {
            // Kiểm tra nhập liệu
            if (request.getUsername() == null || request.getUsername().isEmpty()) {
                return ResponseEntity.status(400)
                        .body(ApiResponse.error("Username không được để trống", 400));
            }
            if (request.getPassword() == null || request.getPassword().isEmpty()) {
                return ResponseEntity.status(400)
                        .body(ApiResponse.error("Password không được để trống", 400));
            }

            // Gọi service để đăng nhập
            Optional<User> user = authService.login(request.getUsername(), request.getPassword());

            if (user.isPresent()) {
                User loginUser = user.get();
                LoginResponse response = LoginResponse.builder()
                        .userId(loginUser.getId())
                        .username(loginUser.getUsername())
                        .fullName(loginUser.getFullName())
                        .email(loginUser.getEmail())
                        .success(true)
                        .message("Đăng nhập thành công")
                        .build();

                return ResponseEntity.ok(ApiResponse.success(response, "Đăng nhập thành công"));
            } else {
                log.warn("Đăng nhập thất bại cho username: " + request.getUsername());
                return ResponseEntity.status(401)
                        .body(ApiResponse.error("Sai tài khoản hoặc mật khẩu", 401));
            }
        } catch (Exception e) {
            log.error("Lỗi đăng nhập: ", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("Lỗi đăng nhập", 500));
        }
    }

    /**
     * Kiểm tra trạng thái kết nối
     * GET /api/auth/health
     */
    @GetMapping("/health")
    public ResponseEntity<ApiResponse<String>> health() {
        return ResponseEntity.ok(ApiResponse.success("OK", "Backend đang chạy"));
    }
}