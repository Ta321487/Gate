package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.sql.Timestamp;
import java.util.List;
import java.util.Map;

@Mapper
public interface SeatMapper {
    @Select("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='cinema_seat'")
    Integer countTable();

    @Select("SELECT id, title, price_yuan AS author, hall_note AS isbn, category_id AS categoryId, stock, status, "
            + "cover_url AS coverUrl, seat_rows AS seatRows, seat_cols AS seatCols, "
            + "DATE_FORMAT(start_at, '%Y-%m-%d %H:%i:%s') AS startAt "
            + "FROM cinema_show WHERE status='available' AND stock>0 "
            + "AND (start_at IS NULL OR start_at > NOW()) ORDER BY id DESC")
    List<Map<String, Object>> listOpenShows();

    @Select("SELECT id, title, price_yuan AS author, hall_note AS isbn, category_id AS categoryId, stock, status, "
            + "cover_url AS coverUrl, seat_rows AS seatRows, seat_cols AS seatCols, "
            + "DATE_FORMAT(start_at, '%Y-%m-%d %H:%i:%s') AS startAt "
            + "FROM cinema_show WHERE id=#{id}")
    Map<String, Object> getShow(long id);

    @Select("SELECT COUNT(*) FROM cinema_seat WHERE show_id=#{showId}")
    Integer countSeats(long showId);

    @Select("SELECT COUNT(*) FROM cinema_seat WHERE show_id=#{showId} AND status='sold'")
    Integer countSold(long showId);

    @Insert("INSERT IGNORE INTO cinema_seat (show_id, seat_code, status) VALUES (#{showId}, #{seatCode}, 'free')")
    int insertSeat(@Param("showId") long showId, @Param("seatCode") String seatCode);

    @Delete({
        "<script>",
        "DELETE FROM cinema_seat WHERE show_id=#{showId} AND status='free'",
        "<if test='codes != null and codes.size() &gt; 0'>",
        " AND seat_code NOT IN ",
        "<foreach collection='codes' item='c' open='(' separator=',' close=')'>#{c}</foreach>",
        "</if>",
        "</script>"
    })
    int deleteFreeOutside(@Param("showId") long showId, @Param("codes") List<String> codes);

    @Update("UPDATE cinema_show SET stock=#{stock} WHERE id=#{showId}")
    int updateShowStock(@Param("showId") long showId, @Param("stock") int stock);

    @Update("UPDATE cinema_show SET status='unavailable' "
            + "WHERE status='available' AND start_at IS NOT NULL AND start_at <= NOW()")
    int expirePastShows();

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

    @Update("UPDATE cinema_seat SET status='free', username=NULL, order_id=NULL, sold_at=NULL WHERE order_id=#{orderId} AND status='sold'")
    int releaseByOrder(long orderId);
}
