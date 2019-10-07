package de.tu_dresden.selis.pubsub;

/**
 * Callback interface allows handling new messages.
 * 
 * @author      Wojciech Ozga <wojciech.ozga@tu-dresden.de>
 * @since       0.1
 */
public interface Callback {

    void onMessage(Message message);

}
