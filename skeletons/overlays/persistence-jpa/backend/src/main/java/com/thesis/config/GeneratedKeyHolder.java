package com.thesis.config;

public class GeneratedKeyHolder implements KeyHolder {

    private Number key;

    @Override
    public Number getKey() {
        return key;
    }

    @Override
    public void setKey(Object key) {
        if (key == null) {
            this.key = null;
        } else if (key instanceof Number n) {
            this.key = n;
        } else {
            try {
                this.key = Long.valueOf(String.valueOf(key));
            } catch (NumberFormatException e) {
                this.key = null;
            }
        }
    }
}
