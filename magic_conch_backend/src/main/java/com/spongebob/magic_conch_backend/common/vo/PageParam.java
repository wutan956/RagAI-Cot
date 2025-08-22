package com.spongebob.magic_conch_backend.common.vo;

import java.io.Serializable;
// 通用分页参数对象，用来接收前端传来的“第几页、每页几条、按什么字段排序”，
// 后端拿到后直接用于 MyBatis-Plus、Spring Data Pageable 等分页查询
public class PageParam implements Serializable {
    private static final long serialVersionUID = 1L;
    // 当前页码，默认值 1（第一页）
    private Integer pageNum = 1;
    // 每页条数，默认值 10
    private Integer pageSize = 10;
    // 排序字段（SQL 中的 order by 子句），可选
    private String orderBy;

    public Integer getPageNum() {
        return pageNum;
    }

    public void setPageNum(Integer pageNum) {
        this.pageNum = pageNum;
    }

    public Integer getPageSize() {
        return pageSize;
    }

    public void setPageSize(Integer pageSize) {
        this.pageSize = pageSize;
    }

    public String getOrderBy() {
        return orderBy;
    }

    public void setOrderBy(String orderBy) {
        this.orderBy = orderBy;
    }
} 