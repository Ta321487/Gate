package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.sql.Timestamp;
import java.util.List;
import java.util.Map;

@Mapper
public interface SeatMapper {
    @Select("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='cinema_seat'")
    Integer countTable();

    @Select("SELECT id, title, author, isbn, category_id AS categoryId, stock, status, cover_url AS coverUrl FROM cinema_show WHERE status='available' AND stock>0 ORDER BY id DESC")
    List<Map<String, Object>> listOpenShows();

    @Select("SELECT id, title, author, isbn, category_id AS categoryId, stock, status, cover_url AS coverUrl FROM cinema_show WHERE id=#{id}")
    Map<String, Object> getShow(long id);

    @Select("SELECT COUNT(*) FROM cinema_seat WHERE show_id=#{showId}")
    Integer countSeats(long showId);

    @Insert("INSERT INTO cinema_seat (show_id, seat_code, status) VALUES (#{showId}, #{seatCode}, 'free')")
    int insertSeat(@Param("showId") long showId, @Param("seatCode") String seatCode);

    @Select("SELECT id, show_id AS showId, seat_code AS seatCode, status, username, order_id AS orderId, sold_at AS soldAt FROM cinema_seat WHERE show_id=#{showId} ORDER BY seat_code")
    List<Map<String, Object>> listSeats(long showId);

    @Select("SELECT COUNT(*) FROM cinema_seat WHERE show_id=#{showId} AND seat_code=#{seatCode} AND status='free'")
    Integer countFreeSeat(@Param("showId") long showId, @Param("seatCode") String seatCode);

    @Update("UPDATE cinema_seat SET status='sold', username=#{username}, order_id=#{orderId}, sold_at=#{soldAt} WHERE show_id=#{showId} AND seat_code=#{seatCode} AND status='free'")
    int sellSeat(
            @Param("showId") long showId,
            @Param("seatCode") String seatCode,
            @Param("username") String username,
            @Param("orderId") long orderId,
            @Param("soldAt") Timestamp soldAt);
}
