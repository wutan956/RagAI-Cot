package com.spongebob.magic_conch_backend;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

// 引导类，就是整个项目的入口，写的方式很固定。函数的名字要和文件名一致
@SpringBootApplication
public class MagicConchBackendApplication {

    public static void main(String[] args) {
        SpringApplication.run(MagicConchBackendApplication.class, args);
    }

}
