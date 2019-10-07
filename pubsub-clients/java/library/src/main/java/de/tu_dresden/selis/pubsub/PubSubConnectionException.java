package de.tu_dresden.selis.pubsub;

/**
 * Exception thrown when the connection with the PubSub server fails.
 * 
 * @author      Wojciech Ozga <wojciech.ozga@tu-dresden.de>
 * @since       0.1
 */
public class PubSubConnectionException extends PubSubException {

    public PubSubConnectionException() {
    }

    public PubSubConnectionException(String message) {
        super(message);
    }

    public PubSubConnectionException(String message, Throwable cause) {
        super(message, cause);
    }

    public PubSubConnectionException(Throwable cause) {
        super(cause);
    }

    public PubSubConnectionException(String message, Throwable cause, boolean enableSuppression, boolean writableStackTrace) {
        super(message, cause, enableSuppression, writableStackTrace);
    }
}
