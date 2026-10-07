package com.iot.backend.service;

import com.iot.backend.entity.User;
import com.iot.backend.repository.UserRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.util.Optional;

/**
 * Auth Service - Quản lý xác thực người dùng
 */
@Slf4j
@Service
public class AuthService {

    @Autowired
    private UserRepository userRepository;

    /**
     * Đăng nhập người dùng
     */
    public Optional<User> login(String username, String password) {
        Optional<User> user = userRepository.findByUsername(username);
        
        if (user.isPresent()) {
            // Kiểm tra mật khẩu (so sánh hash)
            String passwordHash = hashPassword(password);
            if (user.get().getPasswordHash().equals(passwordHash)) {
                log.info("Đăng nhập thành công: " + username);
                return user;
            }
        }
        
        log.warn("Đăng nhập thất bại: " + username);
        return Optional.empty();
    }

    /**
     * Đăng ký người dùng mới
     */
    public User register(String username, String password, String fullName, String email) {
        Optional<User> existingUser = userRepository.findByUsername(username);
        
        if (existingUser.isPresent()) {
            log.warn("Người dùng đã tồn tại: " + username);
            return null;
        }

        User user = new User();
        user.setUsername(username);
        user.setPasswordHash(hashPassword(password));
        user.setFullName(fullName);
        user.setEmail(email);
        user.setCreatedAt(LocalDateTime.now());

        userRepository.save(user);
        log.info("Đăng ký người dùng thành công: " + username);
        return user;
    }

    /**
     * Mã hóa mật khẩu bằng SHA-256
     */
    private String hashPassword(String password) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] encodedhash = digest.digest(password.getBytes());
            StringBuilder hexString = new StringBuilder();

            for (byte b : encodedhash) {
                String hex = Integer.toHexString(0xff & b);
                if (hex.length() == 1) hexString.append('0');
                hexString.append(hex);
            }
            return hexString.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("Lỗi mã hóa mật khẩu", e);
        }
    }
}
