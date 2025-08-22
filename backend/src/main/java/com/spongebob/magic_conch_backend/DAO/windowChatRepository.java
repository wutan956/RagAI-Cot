package com.spongebob.magic_conch_backend.DAO;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;

// 继承这个接口，里面有些东西可以直接用
// 继承自 Spring Data JPA 提供的 JpaRepository 接口，获得对数据库的CRUD（增删改查）操作能力。
// 自动生成该接口的代理实现类（无需手动编写）
// 实体类是Student，Long 是该实体主键的数据类型（通常是数据库的自增 ID）
@Repository
public interface windowChatRepository  extends JpaRepository<WindowChat,Long> {
    //通过查找Email来返回student，
    // 对于简单的sql语句。按照JPA规定的方法命名，就不需要自己写sql语句，比如这里的findBy后面加上Email
    // JPA 方法命名规则： 方法名以 findBy 开头，后面跟实体字段名 Email（注意大小写与实体字段一致）
    // 返回 List<Student> 表示查多条
    List<WindowChat> findByName(String name);
    List<WindowChat> findAll();
    List<WindowChat> deleteByName(String name);
}

