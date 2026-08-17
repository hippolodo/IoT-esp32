package com.iot.backend.controller;

import com.iot.backend.dto.LoginRequest;
import com.iot.backend.entity.User;
import com.iot.backend.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/auth")
@CrossOrigin(origins = "*")
public class AuthController {

    @Autowired
    private UserRepository userRepository;

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody LoginRequest request) {
        // Tìm user theo username
        User user = userRepository.findByUsername(request.getUsername()).orElse(null);

        // Kiểm tra tồn tại và so khớp mật khẩu
        if (user == null || !user.getPasswordHash().equals(request.getPassword())) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                    .body(Map.of("message", "Sai tài khoản hoặc mật khẩu!"));
        }

        // Đăng nhập thành công, trả về thông tin user
        return ResponseEntity.ok(Map.of(
                "status", "success",
                "message", "Đăng nhập thành công!",
                "user", Map.of(
                        "id", user.getId(),
                        "username", user.getUsername(),
                        "fullName", user.getFullName(),
                        "email", user.getEmail()
                )
        ));
    }
}