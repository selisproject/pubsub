package de.tu_dresden.selis.pubsub;

/**
 * Exception thrown when invalid arguments are provided to the subscription rules.
 * 
 * @author      Wojciech Ozga <wojciech.ozga@tu-dresden.de>
 * @since       0.1
 */
public class PubSubArgumentException extends PubSubException {

    public PubSubArgumentException() {
    }

    public PubSubArgumentException(String message) {
        super(message);
    }

    public PubSubArgumentException(String message, Throwable cause) {
        super(message, cause);
    }

    public PubSubArgumentException(Throwable cause) {
        super(cause);
    }

    public PubSubArgumentException(String message, Throwable cause, boolean enableSuppression, boolean writableStackTrace) {
        super(message, cause, enableSuppression, writableStackTrace);
    }
}
